<script setup lang="ts">
import { ref } from "vue";
import { demo } from "./api/client";
const menu = ref(false);
</script>
<template>
  <q-layout view="hHh Lpr fFf">
    <q-header class="app-header">
      <q-toolbar>
        <q-btn
          flat
          round
          icon="menu"
          aria-label="Abrir navegação"
          class="mobile-menu"
          @click="menu = !menu"
        />
        <router-link to="/" class="brand">
          <span class="brand-symbol">a</span>
          antecipe
          <span class="brand-period">.</span>
        </router-link>
        <span class="header-divider" />
        <span class="header-caption">CRÉDITO EM MOVIMENTO</span>
        <q-space />
        <span class="environment-tag">
          <span class="status-dot" />
          {{
            demo ? "Demonstração · dados de exemplo" : "Ambiente de integração"
          }}
        </span>
        <div class="avatar">AC</div>
      </q-toolbar>
    </q-header>
    <q-drawer v-model="menu" show-if-above :width="240" class="app-sidebar">
      <div class="workspace-label">
        WORKSPACE
        <span>Gestão de recebíveis</span>
      </div>
      <div class="nav-label">OPERAÇÕES</div>
      <q-list padding>
        <q-item clickable to="/" exact active-class="nav-active">
          <q-item-section avatar>
            <q-icon name="space_dashboard" />
          </q-item-section>
          <q-item-section>Visão geral</q-item-section>
        </q-item>
        <q-item clickable to="/novo" active-class="nav-active">
          <q-item-section avatar><q-icon name="upload_file" /></q-item-section>
          <q-item-section>Importar recebíveis</q-item-section>
        </q-item>
        <q-item clickable to="/fundos" active-class="nav-active">
          <q-item-section avatar>
            <q-icon name="account_balance" />
          </q-item-section>
          <q-item-section>Fundos e regras</q-item-section>
        </q-item>
      </q-list>
      <div class="sidebar-bottom">
        <q-icon name="verified_user" size="26px" />
        <strong>Decisões com clareza.</strong>
        <p>
          Da importação ao resultado,
          <br />
          cada etapa explicada.
        </p>
        <span>ANTECIPE / HACKATHON KANASTRA</span>
      </div>
    </q-drawer>
    <q-page-container>
      <main class="main-content"><router-view :key="$route.fullPath" /></main>
      <footer>
        Antecipe
        <span>Infraestrutura para antecipar possibilidades.</span>
        <span>Contrato v1.0.0</span>
      </footer>
    </q-page-container>
  </q-layout>
</template>
