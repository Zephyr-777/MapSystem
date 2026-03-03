<template>
  <RoleSwitcher v-if="isAuthenticated" />
  <router-view />
</template>

<script setup lang="ts">
import RoleSwitcher from '@/components/layout/RoleSwitcher.vue';
import { useAuthStore } from '@/stores/auth';
import { storeToRefs } from 'pinia';

const authStore = useAuthStore();
const { isAuthenticated } = storeToRefs(authStore);
</script>
