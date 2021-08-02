import * as path from "path";

import * as HtmlWebpackPlugin from "html-webpack-plugin";
import type * as webpack from "webpack";

const webpackConfig: webpack.Configuration = {
  context: path.resolve(__dirname, "../src"),
  // @ts-ignore
  devServer: {
    historyApiFallback: true,
  },
  entry: path.resolve(__dirname, "../src/index.tsx"),
  module: {
    rules: [
      {
        generator: {
          filename: ({ filename }: { filename: string }) =>
            /[\\/]favicon\.ico$/.test(filename) ? "[name][ext]" : "[hash][ext]",
        },
        test: /\.(gif|ico|jpg|mp3|otf|png|svg|woff2?)$/,
        type: "asset/resource",
      },
      {
        loader: "style-loader",
        test: /\.s?css$/,
      },
      {
        loader: "css-loader",
        test: /\.css$/,
      },
      {
        // This check is permissive by design, as the web-ui library
        // may be symlinked when using the local development build.
        include: path => path.includes("web-ui"),
        loader: "css-loader",
        options: {
          importLoaders: 1,
          modules: {
            localIdentName: "web-ui__[name]--[local]",
          },
        },
        test: /\.scss$/,
      },
      {
        include: path => !path.includes("web-ui"),
        loader: "css-loader",
        options: {
          importLoaders: 1,
          modules: {
            localIdentName: "[name]--[local]",
          },
        },
        test: /\.scss$/,
      },
      {
        loader: "sass-loader",
        options: {
          sassOptions: {
            // We have to set the `outputStyle` explicitly to prevent
            // it defaulting to `compressed` when using webpack in
            // production mode. This would delete (multiline) comments
            // whereas we want to process these with cssnano instead.
            outputStyle: "expanded",
          },
        },
        test: /\.scss$/,
      },
      {
        loader: "ts-loader",
        test: /\.tsx?$/,
      },
    ],
  },
  output: {
    publicPath: "/",
  },
  plugins: [new HtmlWebpackPlugin({ template: "index.html" })],
  resolve: {
    extensions: [".ts", ".tsx", ".js"],
    modules: [
      path.resolve(__dirname, "../src"),
      path.resolve(__dirname, "../node_modules"),
    ],
  },
};

export default webpackConfig;
