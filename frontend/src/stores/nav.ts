import { ref } from 'vue'
import { defineStore } from 'pinia'

export type PageName = 'dashboard' | 'spatial' | 'synergy' | 'temporal'

export const useNavStore = defineStore('nav', () => {
  const currentPage = ref<PageName>('dashboard')
  const go = (name: PageName) => { currentPage.value = name }
  return { currentPage, go }
})