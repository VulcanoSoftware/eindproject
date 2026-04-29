/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'MultiDisk FileBalancer Docs',
  tagline: 'Structured documentation for scalable multi-disk orchestration',
  favicon: 'img/favicon.ico',

  // De URL waar je site op komt te staan
  url: 'https://eindproject.vercel.app',
  baseUrl: '/',

  // BELANGRIJK: Voorkomt dat de build faalt door gebroken links naar ./intro
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
          routeBasePath: '/', // Dit maakt de docs je landingspagina
          sidebarPath: require.resolve('./sidebars.js'),
        },
        blog: false, // Blog uitgeschakeld voor een pure documentatie-site
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
            sidebarId: 'tutorialSidebar',
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
