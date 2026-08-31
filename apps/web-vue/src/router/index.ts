import { createRouter, createWebHistory } from "vue-router";

import DashboardView from "../views/DashboardView.vue";
import RepositoriesView from "../views/RepositoriesView.vue";
import ModelsView from "../views/ModelsView.vue";
import ArenaView from "../views/ArenaView.vue";
import BenchmarksView from "../views/BenchmarksView.vue";
import AgentsView from "../views/AgentsView.vue";
import PlaygroundView from "../views/PlaygroundView.vue";

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: DashboardView },
    { path: "/repositories", component: RepositoriesView },
    { path: "/models", component: ModelsView },
    { path: "/arena", component: ArenaView },
    { path: "/benchmarks", component: BenchmarksView },
    { path: "/agents", component: AgentsView },
    { path: "/playground", component: PlaygroundView },
  ],
});