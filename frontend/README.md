# Comment System Frontend

A modern Vue.js Single Page Application (SPA) for managing user comments.

## Features

- **Real-time Comments** - Post and view comments seamlessly
- **User Management** - User identification and profiles
- **Responsive Design** - Works on desktop and mobile
- **Modern Stack** - Vue 3, Pinia, Vue Router, Vite
- **TypeScript Ready** - Easy to migrate to TypeScript
- **Testing** - Unit tests with Vitest
- **Beautiful UI** - Clean and modern interface

## Tech Stack

- **Frontend Framework:** Vue.js 3
- **State Management:** Pinia
- **Routing:** Vue Router
- **Build Tool:** Vite
- **HTTP Client:** Axios
- **Testing:** Vitest + Vue Test Utils
- **Linting:** ESLint + Prettier

## Quick Start

### Prerequisites

- Node.js >= 18.0.0
- npm >= 8.0.0

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Development

```bash
# Run development server
npm run dev

# Run tests
npm run test

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage

# Lint and format code
npm run lint
npm run format
```

## Project Structure

``
frontend/
├── public/                 # Static assets
├── src/
│   ├── assets/             # Images, styles, etc.
│   ├── components/         # Reusable Vue components
│   │   ├── CommentForm.vue
│   │   ├── CommentItem.vue
│   │   └── CommentsList.vue
│   ├── views/              # Page components
│   │   ├── Home.vue
│   │   └── Comments.vue
│   ├── router/             # Vue Router config
│   ├── store/              # Pinia stores
│   │   └── comments.js
│   ├── services/           # API services
│   │   └── api.js
│   ├── utils/              # Helper functions
│   ├── tests/              # Unit tests
│   ├── App.vue             # Root component
│   └── main.js             # Application entry point
├── index.html              # HTML template
├── package.json            # Dependencies and scripts
├── vite.config.js          # Vite configuration
├── vitest.config.js        # Test configuration
└── .env.development        # Environment variables
``

## Components

### CommentForm

Form component for posting new comments with validation.

### CommentsList

Displays a list of comments with pagination support.

### CommentItem

Individual comment display with like functionality and user info.

## State Management

The application uses Pinia for state management with the following stores:

- **Comments Store** (`src/store/comments.js`)
  - Manages comment data
  - Handles API calls
  - Pagination and loading states

## API Integration

The frontend communicates with the Django backend through REST API:

- `GET /api/comments/` - Fetch comments
- `POST /api/comments/` - Create comment
- `PUT /api/comments/{id}/` - Update comment
- `DELETE /api/comments/{id}/` - Delete comment
- `POST /api/comments/{id}/like/` - Like comment

## Environment Variables

```bash
# .env.development
VITE_API_URL=http://localhost:8000/api
VITE_APP_ENV=development
VITE_ENABLE_ANALYTICS=true
VITE_DEBUG_MODE=true
```

## Testing

The project includes comprehensive tests:

```bash
# Run all tests
npm run test

# Run tests in watch mode
npm run test -- --watch

# Run tests with coverage
npm run test:coverage

# Run tests with UI
npm run test:ui
```

## Deployment

Development

```bash
npm run dev
```

### Production Build

```bash
npm run build
npm run preview
```

### Docker (Future)

```bash
# Build image
docker build -t comment-system-frontend .

# Run container
docker run -p 3000:80 comment-system-frontend
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the License. - perhaps to write any you want
