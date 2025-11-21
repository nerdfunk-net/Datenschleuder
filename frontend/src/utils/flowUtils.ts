import type { Flow, HierarchyAttribute } from '@/composables/useDeploymentWizard'

/**
 * Get flow name from hierarchy attributes
 */
export function getFlowName(flow: Flow, hierarchyConfig: HierarchyAttribute[]): string {
  // Try to get the first hierarchy attribute value as the name
  if (hierarchyConfig.length > 0) {
    const firstAttr = hierarchyConfig[0].name.toLowerCase()
    const srcValue = flow[`src_${firstAttr}`]
    const attrValue = flow[firstAttr]
    return (typeof srcValue === 'string' ? srcValue : null) || 
           (typeof attrValue === 'string' ? attrValue : null) || 
           `Flow ${flow.id}`
  }
  return `Flow ${flow.id}`
}

/**
 * Get top hierarchy value for a flow
 */
export function getTopHierarchyValue(
  flow: Flow,
  side: 'source' | 'destination',
  hierarchyConfig: HierarchyAttribute[]
): string {
  if (hierarchyConfig.length === 0) return 'N/A'

  const topAttr = hierarchyConfig[0].name.toLowerCase()
  const prefix = side === 'source' ? 'src_' : 'dest_'
  const value = flow[`${prefix}${topAttr}`]
  return typeof value === 'string' ? value : 'N/A'
}

/**
 * Get template name from registry flows
 */
export function getTemplateName(
  templateId: number | null,
  registryFlows: Array<Record<string, unknown>>
): string | null {
  if (!templateId) return null

  const template = registryFlows.find((rf) => rf.id === templateId)
  return template ? String(template.flow_name) : `Template ID ${templateId}`
}

/**
 * Find NiFi instance ID for a hierarchy value
 */
export async function getInstanceIdForHierarchyValue(
  hierarchyValue: string,
  topHierarchyAttr: string,
  nifiInstances: Array<Record<string, unknown>>
): Promise<number | null> {
  try {
    // Find the instance that matches the hierarchy attribute and value
    const instance = nifiInstances.find(
      (inst) =>
        inst.hierarchy_attribute === topHierarchyAttr &&
        inst.hierarchy_value === hierarchyValue
    )

    if (instance) {
      console.warn(
        `Found NiFi instance ${instance.id} for ${topHierarchyAttr}=${hierarchyValue}`
      )
      return Number(instance.id)
    }

    console.warn(`No NiFi instance found for ${topHierarchyAttr}=${hierarchyValue}`)
    return null
  } catch (error) {
    console.error('Error getting instance ID:', error)
    return null
  }
}
