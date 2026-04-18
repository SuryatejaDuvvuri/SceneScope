import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  index("routes/home.tsx"),
  route("projects/new", "routes/projects.new.tsx"),
  route("projects/:id", "routes/projects.$id.tsx"),
  route("projects/:id/export", "routes/projects.$id.export.tsx"),
  route("auth/callback", "routes/auth.callback.tsx"),
] satisfies RouteConfig;
