import {Component, h} from "preact";
import Markdown from "preact-markdown";
import {Link} from "react-router-dom";
import {DocProps} from "../components/props";

import indexmarkdown from "../../../docs/index.md";


export default class Docs extends Component<DocProps, {}> {


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
			<Link activeClassName="active" to="/docs">Docs Home</Link>
			<p>Folder: {folder}</p>
			<p>Doc: {doc}</p>
			<Markdown markdown={indexmarkdown} markdownOpts={this.markdownOptions}/>
		</div>;
	}
}
