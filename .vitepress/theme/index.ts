import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import { h } from 'vue'
import FrontmatterMeta from './FrontmatterMeta.vue'
import './custom.css'

export default {
  extends: DefaultTheme,
  Layout: () =>
    h(DefaultTheme.Layout, null, {
      'doc-before': () => h(FrontmatterMeta),
    }),
} satisfies Theme
