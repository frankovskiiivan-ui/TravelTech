// sidebars.js
const sidebars = {
  docs: [
    'index',
    {
      type: 'category',
      label: 'Архитектура',
      items: [
        'architecture/overview',
        'architecture/microservices',
        'architecture/data-flow',
      ],
    },
    {
      type: 'category',
      label: 'API',
      items: [
        'api/rest-api',
        'api/event-driven',
      ],
    },
    {
      type: 'category',
      label: 'База данных',
      items: [
        'database/schema',
        'database/redis-cache',
      ],
    },
    {
      type: 'category',
      label: 'Развертывание',
      items: [
        'deployment/docker-compose',
        'deployment/local-setup',
      ],
    },
  ],
};

module.exports = sidebars;