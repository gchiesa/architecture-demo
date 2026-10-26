import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'
import { buildSidebar } from './sidebar.mjs'

export default withMermaid(
  defineConfig({
    title: 'Architecture Demo Docs',
    description: 'Engineering docs synced from Notion',
    srcDir: '.',
    srcExclude: ['**/CONTRIBUTING.md', '**/node_modules/**'],
    ignoreDeadLinks: true,

    // Keep `README.md` as the source filename everywhere (so folders still
    // render nicely in GitHub's own file browser), but build each one to
    // `index.html` so a static host like GitHub Pages serves it for the
    // directory URL (e.g. `/ADR/foo/`) without a server-side rewrite rule.
    rewrites: {
      'README.md': 'index.md',
      ':path(.*)/README.md': ':path/index.md',
    },

    // The prev/next footer pairing is based on sidebar order, which isn't a
    // meaningful reading sequence for these independently-authored docs -
    // disable it site-wide rather than per page.
    transformPageData(pageData) {
      pageData.frontmatter.prev = false
      pageData.frontmatter.next = false
    },

    themeConfig: {
      nav: [{ text: 'Home', link: '/' }],
      sidebar: buildSidebar(),
      outline: { level: [2, 3] },
      search: { provider: 'local' },
      socialLinks: [{ icon: 'github', link: 'https://github.com/gchiesa/architecture-demo' }],
      editLink: {
        pattern: 'https://github.com/gchiesa/architecture-demo/edit/main/:path',
        text: 'Edit this page on GitHub',
      },
    },

    mermaid: {
      theme: 'default',
    },
  }),
)
