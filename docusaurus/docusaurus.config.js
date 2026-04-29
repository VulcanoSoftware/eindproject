module.exports = {
  title: 'MultiDisk FileBalancer Docs',
  tagline: 'Structured documentation for scalable multi-disk orchestration',
  favicon: 'img/favicon.ico',
  url: 'https://example.com',
  baseUrl: '/',
  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },
  markdown: {
    mermaid: true,
  },
  themes: ['@docusaurus/theme-mermaid'],
  presets: [
    [
      '@docusaurus/preset-classic',
      {
        docs: {
          routeBasePath: '/',
          sidebarPath: require.resolve('./sidebars.js'),
        },
        blog: false,
        pages: false,
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      },
    ],
  ],
  themeConfig: {
    navbar: {
      title: 'MultiDisk FileBalancer',
      items: [
        {to: '/', label: 'Docs', position: 'left'},
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Documentation',
          items: [{label: 'Intro', to: '/'}],
        },
      ],
      copyright: `Copyright ${new Date().getFullYear()} MultiDisk FileBalancer`,
    },
  },
};
