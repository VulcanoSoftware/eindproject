/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'MultiDisk FileBalancer Docs',
  tagline: 'Structured documentation for scalable multi-disk orchestration',
  favicon: 'img/favicon.ico',

  url: 'https://eindproject.vercel.app',
  baseUrl: '/',

  onBrokenLinks: 'warn',
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
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          routeBasePath: '/', 
          sidebarPath: require.resolve('./sidebars.js'),
        },
        blog: false,
        pages: false,
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      navbar: {
        title: 'MultiDisk FileBalancer',
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'docsSidebar', // DIT IS GEFIXT (was tutorialSidebar)
            position: 'left',
            label: 'Documentation',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Documentation',
            items: [
              {
                label: 'Intro',
                to: '/',
              },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} MultiDisk FileBalancer. Built with Docusaurus.`,
      },
    }),
};

module.exports = config;
