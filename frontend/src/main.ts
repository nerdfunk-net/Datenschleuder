import { createApp, type Component } from "vue";
import router from "./router";
import pinia from "./stores";

// Import Roboto font locally for air-gapped environments
import "@fontsource/roboto/100.css";
import "@fontsource/roboto/300.css";
import "@fontsource/roboto/400.css";
import "@fontsource/roboto/500.css";
import "@fontsource/roboto/700.css";
import "@fontsource/roboto/900.css";

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
app.component("BButton", BButton as Component);
app.component("BRow", BRow as Component);
app.component("BCol", BCol as Component);
app.component("BCard", BCard as Component);
app.component("BCardBody", BCardBody as Component);
app.component("BCardHeader", BCardHeader as Component);
app.component("BFormCheckboxGroup", BFormCheckboxGroup as Component);
app.component("BFormRadioGroup", BFormRadioGroup as Component);
app.component("BFormInput", BFormInput as Component);
app.component("BFormCheckbox", BFormCheckbox as Component);
app.component("BFormSelect", BFormSelect as Component);
app.component("BFormTextarea", BFormTextarea as Component);
app.component("BFormFile", BFormFile as Component);
app.component("BFormInvalidFeedback", BFormInvalidFeedback as Component);
app.component("BInputGroup", BInputGroup as Component);
app.component("BInputGroupText", BInputGroupText as Component);
app.component("BModal", BModal as Component);
app.component("BCollapse", BCollapse as Component);
app.component("BDropdown", BDropdown as Component);
app.component("BDropdownItem", BDropdownItem as Component);
app.component("BDropdownItemButton", BDropdownItemButton as Component);
app.component("BDropdownHeader", BDropdownHeader as Component);
app.component("BDropdownDivider", BDropdownDivider as Component);
app.component("BTooltip", BTooltip as Component);
app.component("BPopover", BPopover as Component);
app.component("BProgress", BProgress as Component);
app.component("BProgressBar", BProgressBar as Component);
app.component("BTable", BTable as Component);
app.component("BTabs", BTabs as Component);
app.component("BTab", BTab as Component);
app.component("BCarousel", BCarousel as Component);
app.component("BCarouselSlide", BCarouselSlide as Component);
app.component("BPagination", BPagination as Component);
app.component("BAlert", BAlert as Component);
app.component("BSpinner", BSpinner as Component);
app.component("BLink", BLink as Component);

app.component("FontAwesomeIcon", FontAwesomeIcon);

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
