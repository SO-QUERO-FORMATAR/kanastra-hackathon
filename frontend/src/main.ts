import { createApp } from "vue";
import { Quasar, Notify, Dialog } from "quasar";
import lang from "quasar/lang/pt-BR";
import "@quasar/extras/material-icons/material-icons.css";
import "quasar/src/css/index.sass";
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/syne/500.css";
import "@fontsource/syne/600.css";
import "./style.css";
import App from "./App.vue";
import { router } from "./router";
createApp(App)
  .use(Quasar, {
    plugins: { Notify, Dialog },
    lang,
    config: {
      brand: {
        primary: "#193C32",
        secondary: "#14735A",
        positive: "#14735A",
        negative: "#9B1C1C",
        warning: "#92400E",
      },
    },
  })
  .use(router)
  .mount("#app");
