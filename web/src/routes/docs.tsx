import {h, Component} from "preact";
import Markdown from "preact-markdown";
import { Link } from "preact-router";

import indexmarkdown from "../../../docs/index.md";


export default class Docs extends Component<{}, {}> {

	componentDidMount() {
		console.log("We mounted!");
	};

	markdownOptions = {
		"baseUrl": "docs/",
		"headerIds": true,
		"breaks": true
	};

	render() {
		return <div class="docsMain">
			<h1>Docs</h1>
			<Link activeClassName="active" href="/docs">Docs Home</Link>
			<Markdown markdown={indexmarkdown} markdownOpts={this.markdownOptions}></Markdown>
		</div>;
	}
}
