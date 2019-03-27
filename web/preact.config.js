import {resolve} from "path";
import ForkTsCheckerWebpackPlugin from "fork-ts-checker-webpack-plugin";

export default function (config, env, helpers) {
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

    // TypeScript plugin
    config.module.rules.unshift({
        enforce: 'pre',
        test: /\.tsx?$/,
        loader: 'ts-loader',
        options: {
            transpileOnly: true
        }
    });

    config.plugins.push(
        new ForkTsCheckerWebpackPlugin({
            tslint: false, 
            useTypescriptIncrementalApi: true,
            tsconfig: "../tsconfig.json"
        })
    )

    if (config.devServer)
        config.devServer.headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "x-requested-with",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Credentials": "true"
        }
}