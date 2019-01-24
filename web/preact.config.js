import preactCliTypeScript from "preact-cli-plugin-typescript";
/**
 * Function that mutates original webpack config.
 * Supports asynchronous changes when promise is returned.
 *
 * @param {object} config - original webpack config.
 * @param {object} env - options passed to CLI.
 * @param {WebpackConfigHelpers} helpers - object with useful helpers when working with config.
 **/
export default function (config, env, helpers) {
	preactCliTypeScript(config);

	module: {
		rules: [
            
			{ test: /\.(s*)css$/, use: ["sass-loader", "style-loader", "css-loader"] }
		];
	}

}