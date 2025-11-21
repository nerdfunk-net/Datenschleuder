import type {
  ProcessGroupPath,
  Flow,
  HierarchyAttribute,
  DeploymentSettings
} from '@/composables/useDeploymentWizard'

/**
 * Format process group paths for display in dropdown
 */
export function formatPathsForDisplay(
  paths: ProcessGroupPath[]
): Array<{ id: string; pathDisplay: string }> {
  return paths.map((pg) => {
    // Reverse the path array so root is first and deepest is last
    const pathNames = pg.path
      .slice()
      .reverse()
      .map((p) => p.name)
      .join(' → ')
    return {
      id: pg.id,
      pathDisplay: pathNames
    }
  })
}

/**
 * Get mock paths for development/testing
 */
export function getMockPaths(): Array<{ id: string; pathDisplay: string }> {
  return [
    { id: 'root', pathDisplay: 'NiFi Flow' },
    { id: 'pg1', pathDisplay: 'NiFi Flow → Engineering' },
    { id: 'pg2', pathDisplay: 'NiFi Flow → Engineering → DataPipeline' },
    { id: 'pg3', pathDisplay: 'NiFi Flow → Marketing' },
    { id: 'pg4', pathDisplay: 'NiFi Flow → Marketing → Analytics' }
  ]
}

/**
 * Auto-select a process group based on deployment settings and hierarchy
 */
export function autoSelectProcessGroup(
  flow: Flow,
  target: 'source' | 'destination',
  instanceId: number,
  availablePaths: ProcessGroupPath[],
  deploymentSettings: DeploymentSettings,
  hierarchyConfig: HierarchyAttribute[]
): string | null {
  try {
    // Get the search path from deployment settings
    if (
      !deploymentSettings ||
      !deploymentSettings.paths ||
      !deploymentSettings.paths[instanceId]
    ) {
      return null
    }

    const instanceSettings = deploymentSettings.paths[instanceId] as { source_path?: string; dest_path?: string }
    const searchPathId =
      target === 'source'
        ? instanceSettings.source_path
        : instanceSettings.dest_path

    if (!searchPathId) {
      return null
    }

    // Find the search path in available paths
    const searchPath = availablePaths.find((p) => p.id === searchPathId)
    if (!searchPath) {
      return null
    }

    // Get the search path as an array of names (reversed, since path is stored root-first)
    const searchPathNames = searchPath.path
      .slice()
      .reverse()
      .map((p) => p.name)

    // Get hierarchy attributes for this flow, skipping:
    // - Top hierarchy (index 0) - represents the NiFi instance
    // - Last hierarchy (index length-1) - the final process group that will be created during deployment
    // So we use attributes from index 1 to length-2
    const hierarchyAttributes: string[] = []
    const prefix = target === 'source' ? 'src_' : 'dest_'

    for (let i = 1; i < hierarchyConfig.length - 1; i++) {
      const attrName = hierarchyConfig[i].name.toLowerCase()
      const value = flow[`${prefix}${attrName}`]
      if (value && typeof value === 'string') {
        hierarchyAttributes.push(value)
      }
    }

    // Now find a path that:
    // 1. Starts with all elements from searchPathNames
    // 2. Contains all hierarchyAttributes in order
    for (const pg of availablePaths) {
      const pgPathNames = pg.path
        .slice()
        .reverse()
        .map((p) => p.name)

      // Check if path starts with search path
      let startsWithSearchPath = true
      for (let i = 0; i < searchPathNames.length; i++) {
        if (pgPathNames[i] !== searchPathNames[i]) {
          startsWithSearchPath = false
          break
        }
      }

      if (!startsWithSearchPath) {
        continue
      }

      // Check if path contains all hierarchy attributes in order
      let matchesHierarchy = true
      let searchIndex = searchPathNames.length // Start searching after the search path prefix

      for (const attr of hierarchyAttributes) {
        let found = false
        for (let i = searchIndex; i < pgPathNames.length; i++) {
          if (pgPathNames[i] === attr) {
            found = true
            searchIndex = i + 1
            break
          }
        }
        if (!found) {
          matchesHierarchy = false
          break
        }
      }

      if (matchesHierarchy) {
        return pg.id
      }
    }

    return null
  } catch (error) {
    console.error('Error in autoSelectProcessGroup:', error)
    return null
  }
}

/**
 * Get the hierarchy attribute name for a given process group.
 *
 * The backend builds paths as: configured_path + hierarchy_values
 * We need to determine which hierarchy level the selected PG represents
 * by comparing its path against the configured deployment path.
 *
 * For example:
 * - Configured path: "NiFi Flow/To net1"
 * - Selected PG path: "NiFi Flow/To net1/o1/ou1"
 * - Hierarchy offset: 2 (ou1 is the 2nd level after configured path)
 * - Returns: hierarchy[2] = "datenschleuder_ou"
 */
export function getHierarchyAttributeForProcessGroup(
  processGroupId: string,
  instanceKey: string,
  instanceId: number,
  target: 'source' | 'destination',
  processGroupPaths: Record<string, ProcessGroupPath[]>,
  deploymentSettings: DeploymentSettings,
  hierarchyConfig: HierarchyAttribute[]
): string | null {
  if (!hierarchyConfig.length || !deploymentSettings) return null

  // Find the process group in the paths
  const paths = processGroupPaths[instanceKey] || []
  const selectedPg = paths.find((pg) => pg.id === processGroupId)

  if (!selectedPg || !selectedPg.path || selectedPg.path.length === 0) return null

  // Get configured path for this instance
  const instanceSettings = deploymentSettings.paths?.[instanceId] as { source_path?: { id: string; path: string }; dest_path?: { id: string; path: string } } | undefined
  if (!instanceSettings) return null

  // Get the PathConfig object (contains id and path properties)
  const pathConfig =
    target === 'source' ? instanceSettings.source_path : instanceSettings.dest_path

  if (!pathConfig || !pathConfig.path) return null

  // Extract the path string from the PathConfig object
  const configuredPath = pathConfig.path

  // Build PG path string from the path array (excluding root)
  const pgPathSegments = selectedPg.path
    .filter((p: { name?: string }) => p.name !== 'NiFi Flow') // Exclude root
    .map((p: { name?: string }) => p.name || '')

  // Count configured path segments
  const configuredSegments = configuredPath.split('/').filter((p: string) => p.length > 0)

  // Calculate hierarchy offset: PG segments - configured segments
  // This tells us how many hierarchy levels deep we are after the configured path
  const hierarchyOffset = pgPathSegments.length - configuredSegments.length

  // Map to hierarchy index (accounting for skipped first level)
  // hierarchy[0] = top level (DC) - in configured path
  // hierarchy[1] = second level (O) - first deployed level
  // hierarchy[2] = third level (OU) - second deployed level
  const hierarchyIndex = hierarchyOffset

  if (hierarchyIndex > 0 && hierarchyIndex < hierarchyConfig.length) {
    return hierarchyConfig[hierarchyIndex].name
  }

  return null
}

/**
 * Generate a process group name from template and flow hierarchy
 */
export function generateProcessGroupName(
  flow: Flow,
  target: 'source' | 'destination',
  hierarchyConfig: HierarchyAttribute[],
  template: string = '{last_hierarchy_value}'
): string {
  // Get hierarchy values for this flow
  const prefix = target === 'source' ? 'src_' : 'dest_'
  const hierarchyValues: string[] = []

  for (let i = 0; i < hierarchyConfig.length; i++) {
    const attrName = hierarchyConfig[i].name.toLowerCase()
    const value = flow[`${prefix}${attrName}`]
    hierarchyValues.push(typeof value === 'string' ? value : '')
  }

  // Replace placeholders in template
  let result = template

  // Replace {first_hierarchy_value}
  if (hierarchyValues.length > 0) {
    result = result.replace(/{first_hierarchy_value}/g, hierarchyValues[0])
  }

  // Replace {last_hierarchy_value}
  if (hierarchyValues.length > 0) {
    result = result.replace(/{last_hierarchy_value}/g, hierarchyValues[hierarchyValues.length - 1])
  }

  // Replace {N_hierarchy_value} where N is 1, 2, 3, etc.
  for (let i = 0; i < hierarchyValues.length; i++) {
    const placeholder = `{${i + 1}_hierarchy_value}`
    result = result.replace(
      new RegExp(placeholder.replace(/[{}]/g, '\\$&'), 'g'),
      hierarchyValues[i]
    )
  }

  return result
}

/**
 * Get suggested path hint for a deployment
 */
export function getSuggestedPath(
  flow: Flow,
  side: 'source' | 'destination',
  hierarchyConfig: HierarchyAttribute[]
): string | null {
  // Get the penultimate hierarchy value (e.g., OU)
  if (hierarchyConfig.length < 2) return null

  const secondAttr = hierarchyConfig[1].name.toLowerCase()
  const prefix = side === 'source' ? 'src_' : 'dest_'
  const value = flow[`${prefix}${secondAttr}`]

  return value ? `Contains "${value}"` : null
}

/**
 * Get the selected path display text
 */
export function getSelectedPathDisplay(
  deployment: { availablePaths: Array<{ id: string; pathDisplay: string }>; selectedProcessGroupId: string }
): string {
  const selected = deployment.availablePaths.find(
    (p) => p.id === deployment.selectedProcessGroupId
  )
  return selected?.pathDisplay || 'Not selected'
}
