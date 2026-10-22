<script setup lang="ts">
import { computed } from 'vue'
import { useData } from 'vitepress'

// Same fields docsify's frontmatterAndNotionEditLink plugin hid from the
// meta table - they're either internal (id, content_hash), already shown
// elsewhere (title), surfaced separately (notion_url -> the edit link), or
// VitePress theme config injected by transformPageData (prev/next).
const HIDDEN_KEYS = new Set([
  'id',
  'title',
  'notion_url',
  'doc_url',
  'content_hash',
  'layout',
  'prev',
  'next',
])

const { frontmatter } = useData()

function formatValue(value: unknown): string {
  if (Array.isArray(value)) return value.join(', ')
  if (typeof value === 'string') {
    const dateMatch = value.match(/^(\d{4}-\d{2}-\d{2})T\d{2}:\d{2}/)
    if (dateMatch) return dateMatch[1]
  }
  return String(value)
}

const rows = computed(() => {
  const fm = frontmatter.value ?? {}
  return Object.keys(fm)
    .filter((key) => !HIDDEN_KEYS.has(key) && fm[key] !== undefined && fm[key] !== null && fm[key] !== '')
    .map((key) => ({ label: key.replace(/_/g, ' '), value: formatValue(fm[key]) }))
})

const notionUrl = computed(() => frontmatter.value?.notion_url as string | undefined)
</script>

<template>
  <div v-if="rows.length || notionUrl" class="frontmatter-block">
    <table v-if="rows.length" class="frontmatter-meta">
      <tbody>
        <tr v-for="row in rows" :key="row.label">
          <th>{{ row.label }}</th>
          <td>{{ row.value }}</td>
        </tr>
      </tbody>
    </table>
    <p v-if="notionUrl" class="notion-edit-link">
      <a :href="notionUrl" target="_blank" rel="noopener">✏️ Edit in Notion</a>
    </p>
    <div class="frontmatter-clear" />
  </div>
</template>

<style scoped>
.frontmatter-meta {
  float: right;
  margin: 0 0 1em 1.5em;
  font-size: 0.75em;
  border-collapse: collapse;
}
.frontmatter-meta th,
.frontmatter-meta td {
  border: 1px solid var(--vp-c-brand-1);
  padding: 0.25em 0.6em;
  text-align: left;
  white-space: nowrap;
}
.frontmatter-meta th {
  font-weight: 600;
  background: var(--vp-c-brand-soft);
}
.notion-edit-link {
  text-align: left;
  margin: 0;
}
.notion-edit-link a {
  display: inline-block;
  font-size: 0.8em;
  padding: 0.25em 0.75em;
  border: 1px solid var(--vp-c-brand-1);
  border-radius: 1em;
  text-decoration: none;
}
.frontmatter-clear {
  clear: both;
}
</style>
