import { createApp } from "vue";
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
app.component("BButton", BButton as any);
app.component("BRow", BRow as any);
app.component("BCol", BCol as any);
app.component("BCard", BCard as any);
app.component("BCardBody", BCardBody as any);
app.component("BCardHeader", BCardHeader as any);
app.component("BFormCheckboxGroup", BFormCheckboxGroup as any);
app.component("BFormRadioGroup", BFormRadioGroup as any);
app.component("BFormInput", BFormInput as any);
app.component("BFormCheckbox", BFormCheckbox as any);
app.component("BFormSelect", BFormSelect as any);
app.component("BFormTextarea", BFormTextarea as any);
app.component("BFormFile", BFormFile as any);
app.component("BFormInvalidFeedback", BFormInvalidFeedback as any);
app.component("BInputGroup", BInputGroup as any);
app.component("BInputGroupText", BInputGroupText as any);
app.component("BModal", BModal as any);
app.component("BCollapse", BCollapse as any);
app.component("BDropdown", BDropdown as any);
app.component("BDropdownItem", BDropdownItem as any);
app.component("BDropdownItemButton", BDropdownItemButton as any);
app.component("BDropdownHeader", BDropdownHeader as any);
app.component("BDropdownDivider", BDropdownDivider as any);
app.component("BTooltip", BTooltip as any);
app.component("BPopover", BPopover as any);
app.component("BProgress", BProgress as any);
app.component("BProgressBar", BProgressBar as any);
app.component("BTable", BTable as any);
app.component("BTabs", BTabs as any);
app.component("BTab", BTab as any);
app.component("BCarousel", BCarousel as any);
app.component("BCarouselSlide", BCarouselSlide as any);
app.component("BPagination", BPagination as any);
app.component("BAlert", BAlert as any);
app.component("BSpinner", BSpinner as any);
app.component("BLink", BLink as any);

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
