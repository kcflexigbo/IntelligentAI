# frontend/Dockerfile

# --- Stage 1: Build the React application ---
FROM node:22-alpine as build-stage

WORKDIR /app

# Copy package.json and lock files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application source code
COPY . .

# Build the application for production
RUN npm run build

# --- Stage 2: Serve the application with Nginx ---
FROM nginx:stable-alpine

# Copy the built static files from the build stage
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Copy a custom Nginx configuration to handle SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]