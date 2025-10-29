import { createApp } from "vue";
import router from "./router";
import pinia from "./stores";

// Import the original base.scss which includes all theme styling
import "./assets/base.scss";

// Import vue3-perfect-scrollbar CSS
import "vue3-perfect-scrollbar/style.css";

// Import BootstrapVueNext components
import {
  BButton,
  BRow,
  BCol,
  BCard,
  BCardBody,
  BCardHeader,
  BFormCheckboxGroup,
  BFormRadioGroup,
  BFormInput,
  BFormCheckbox,
  BFormSelect,
  BFormTextarea,
  BFormFile,
  BFormInvalidFeedback,
  BInputGroup,
  BInputGroupText,
  BModal,
  BCollapse,
  BDropdown,
  BDropdownItem,
  BDropdownItemButton,
  BDropdownHeader,
  BDropdownDivider,
  BTooltip,
  BPopover,
  BProgress,
  BProgressBar,
  BTable,
  BTabs,
  BTab,
  BCarousel,
  BCarouselSlide,
  BPagination,
  BAlert,
  BSpinner,
  BLink,
} from "bootstrap-vue-next";

import { createBootstrap } from "bootstrap-vue-next";

// Import FontAwesome (optional - app uses pe-7s icons)
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faCheck, faUser } from "@fortawesome/free-solid-svg-icons";

import App from "./App.vue";

// Add icons to library
library.add(faCheck, faUser);

const app = createApp(App);

app.use(router);
app.use(pinia);
app.use(createBootstrap());

// Register BootstrapVueNext components
app.component("b-button", BButton as any);
app.component("b-row", BRow as any);
app.component("b-col", BCol as any);
app.component("b-card", BCard as any);
app.component("b-card-body", BCardBody as any);
app.component("b-card-header", BCardHeader as any);
app.component("b-form-checkbox-group", BFormCheckboxGroup as any);
app.component("b-form-radio-group", BFormRadioGroup as any);
app.component("b-form-input", BFormInput as any);
app.component("b-form-checkbox", BFormCheckbox as any);
app.component("b-form-select", BFormSelect as any);
app.component("b-form-textarea", BFormTextarea as any);
app.component("b-form-file", BFormFile as any);
app.component("b-form-invalid-feedback", BFormInvalidFeedback as any);
app.component("b-input-group", BInputGroup as any);
app.component("b-input-group-text", BInputGroupText as any);
app.component("b-modal", BModal as any);
app.component("b-collapse", BCollapse as any);
app.component("b-dropdown", BDropdown as any);
app.component("b-dropdown-item", BDropdownItem as any);
app.component("b-dropdown-item-button", BDropdownItemButton as any);
app.component("b-dropdown-header", BDropdownHeader as any);
app.component("b-dropdown-divider", BDropdownDivider as any);
app.component("b-tooltip", BTooltip as any);
app.component("b-popover", BPopover as any);
app.component("b-progress", BProgress as any);
app.component("b-progress-bar", BProgressBar as any);
app.component("b-table", BTable as any);
app.component("b-tabs", BTabs as any);
app.component("b-tab", BTab as any);
app.component("b-carousel", BCarousel as any);
app.component("b-carousel-slide", BCarouselSlide as any);
app.component("b-pagination", BPagination as any);
app.component("b-alert", BAlert as any);
app.component("b-spinner", BSpinner as any);
app.component("b-link", BLink as any);

app.component("font-awesome-icon", FontAwesomeIcon);

// Suppress browser extension errors in development
if (import.meta.env.DEV) {
  const extensionErrorPatterns = [
    "message channel closed",
    "listener indicated an asynchronous response",
    "Extension context invalidated",
    "Could not establish connection",
    "Receiving end does not exist",
  ];

  const isExtensionError = (message: string) => {
    if (!message) return false;
    return extensionErrorPatterns.some((pattern) =>
      message.toLowerCase().includes(pattern.toLowerCase()),
    );
  };

  window.addEventListener("error", (event) => {
    if (
      isExtensionError(event.message) ||
      isExtensionError(event.error?.message)
    ) {
      event.preventDefault();
      return false;
    }
  });

  window.addEventListener("unhandledrejection", (event) => {
    const message = event.reason?.message || event.reason?.toString?.() || "";
    if (isExtensionError(message)) {
      event.preventDefault();
      return false;
    }
  });
}

app.mount("#app");
