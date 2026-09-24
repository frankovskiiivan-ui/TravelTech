// docusaurus.config.js
const config = {
  title: 'TravelTech IROPS',
  tagline: 'Система отслеживания сбоев рейсов и автоматического перепланирования',
  url: 'https://your-username.github.io',
  baseUrl: '/TravelTech-Docs/',
  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',
  favicon: 'img/favicon.ico',
  organizationName: 'your-username',
  projectName: 'TravelTech-Docs',
  trailingSlash: false,

  presets: [
    [
      '@docusaurus/preset-classic',
      {
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          editUrl: 'https://github.com/your-username/TravelTech-Docs/tree/main/',
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      },
    ],
  ],

  themeConfig: {
    navbar: {
      title: 'TravelTech IROPS',
      logo: {
        alt: 'TravelTech Logo',
        src: 'img/logo.svg',
      },
      items: [
        {
          type: 'doc',
          docId: 'index',
          position: 'left',
          label: 'Документация',
        },
        {
          href: 'https://github.com/your-username/TravelTech-Docs',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Документация',
          items: [
            {
              label: 'Архитектура',
              to: '/docs/architecture/overview',
            },
            {
              label: 'API',
              to: '/docs/api/openapi',
            },
          ],
        },
        {
          title: 'Сообщество',
          items: [
            {
              label: 'GitHub',
              href: 'https://github.com/your-username/TravelTech-Docs',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} TravelTech. Built with Docusaurus.`,
    },
  },
};

module.exports = config;