import { resolve } from "path";

export default function(config, env, helpers) {
  const entry = resolve(
    process.cwd(),
    "src",
    "index"
  );

  // Use any `index` file, not just index.js
  config.resolve.alias["preact-cli-entrypoint"] = entry;

  if (env.ssr) {
    config.entry["ssr-bundle"] = entry;
  }

  // typescript plugin
  config.module.rules.unshift({
    enforce: 'pre',
    test: /\.tsx?$/,
    loader: 'awesome-typescript-loader',
    options: {
      useBabel: false,
      useCache: true
    }
  });
}