import { createRouter, createWebHistory } from "vue-router";
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: () => import("./pages/HistoryPage.vue") },
    { path: "/novo", component: () => import("./pages/UploadPage.vue") },
    { path: "/lotes/:id", component: () => import("./pages/LotPage.vue") },
    { path: "/fundos", component: () => import("./pages/FundsPage.vue") },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});
