// Builds the VitePress sidebar straight from `sidebar.yaml` + each synced
// doc's frontmatter, mirroring the grouping logic that used to live in
// `.scripts/generate_sidebar.py` for docsify's `_sidebar.md`. VitePress has
// no client-side `loadSidebar`, so this runs at config-load time (every
// `vitepress dev`/`build`) instead of writing a static file.
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import matter from 'gray-matter'
import yaml from 'js-yaml'

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

function loadConfig() {
  const raw = fs.readFileSync(path.join(REPO_ROOT, 'sidebar.yaml'), 'utf-8')
  return yaml.load(raw)
}

function findReadmes(root) {
  const full = path.join(REPO_ROOT, root)
  if (!fs.existsSync(full)) return []
  const results = []
  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const entryPath = path.join(dir, entry.name)
      if (entry.isDirectory()) walk(entryPath)
      else if (entry.name === 'README.md') results.push(entryPath)
    }
  }
  walk(full)
  return results.sort()
}

function resolveTemplate(templates, defaultTemplate, key, context) {
  const template = (templates && templates[key]) ?? defaultTemplate ?? null
  if (template == null) return null
  const ctx = { ...context, value: key ?? 'unknown' }
  return template.replace(/\{(\w+)\}/g, (_match, name) => String(ctx[name] ?? 'unknown'))
}

function buildSection(section) {
  const files = findReadmes(section.root)
  const groups = new Map()
  const labels = new Map()

  for (const file of files) {
    const { data: fm } = matter(fs.readFileSync(file, 'utf-8'))
    const groupValue = fm[section.group_by]
    const label = resolveTemplate(
      section.group_label_templates,
      section.default_group_label_template ?? 'Other',
      groupValue,
      fm,
    )
    const title = fm.title ?? path.basename(path.dirname(file))
    const relDir = path.relative(REPO_ROOT, path.dirname(file)).split(path.sep).join('/')

    if (!groups.has(groupValue)) groups.set(groupValue, [])
    groups.get(groupValue).push({ text: title, link: `/${relDir}/` })
    labels.set(groupValue, label)
  }

  if (groups.size === 0) return null

  const groupOrder = section.group_order || []
  const orderedKeys = [...groups.keys()].sort((a, b) => {
    const ai = groupOrder.indexOf(a)
    const bi = groupOrder.indexOf(b)
    if (ai !== -1 || bi !== -1) {
      if (ai === -1) return 1
      if (bi === -1) return -1
      return ai - bi
    }
    return labels.get(a).localeCompare(labels.get(b))
  })

  return {
    text: section.label,
    collapsed: true,
    items: orderedKeys.map((key) => ({
      text: labels.get(key),
      collapsed: true,
      items: [...groups.get(key)].sort((a, b) => a.text.localeCompare(b.text)),
    })),
  }
}

export function buildSidebar() {
  const config = loadConfig()
  const items = [{ text: 'Home', link: '/' }]
  for (const section of config.sections) {
    const built = buildSection(section)
    if (built) items.push(built)
  }
  return items
}
