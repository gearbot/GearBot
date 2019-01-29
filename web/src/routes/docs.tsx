import {Component, h} from "preact";
import Markdown from "preact-markdown";
import {Link} from "preact-router";
import {Docprops} from "../components/props";

import indexmarkdown from "../../../docs/index.md";


export default class Docs extends Component<Docprops, {}> {

	componentDidMount() {
		console.log("We mounted!");
	};

	markdownOptions = {
		"baseUrl": "docs/",
		"headerIds": true,
		"breaks": true
	};

	render({folder, doc}) {
		return <div class="docsMain">
			<h1>Docs</h1>
			<p>Folder: {folder}</p>
			<p>Doc: {doc}</p>
			<Link activeClassName="active" href="/docs">Docs Home</Link>
			<Markdown markdown={indexmarkdown} markdownOpts={this.markdownOptions}></Markdown>
		</div>;
	}
}
