import {Component, h} from "preact";
import Markdown from "preact-markdown";
import {Docprops} from "../components/props";
import {DocState} from "../components/state";
import menu from "../docs/menu"
import {Link} from "preact-router/match";


export default class Docs extends Component<Docprops, DocState> {

	componentDidMount() {
		let url: RequestInfo;
		console.log(menu);
		if (this.props.doc == "")
			if (this.props.folder == "")
				url = "index.md";
			else
				url = this.props.folder + ".md";
		else
			url = this.props.doc + ".md";
		fetch(url).then(data => {
			console.log("We made a request and got a code of " + data.status)
			if (data.status == 200) {
				data.text().then(text => this.setState({markdown: text}))
			} else {
				this.setState({markdown: "# 404"});
			}
		});
	};

	markdownOptions = {
		"headerIds": true,
		"breaks": true
	};

	render({doc}) {
		let navmenu = [];
		for (var prop in menu) {
			let value = menu[prop];
			let target = typeof value == "string" ? value : prop;
			navmenu.push(<li><Link activeClassName={"active"} href={"/docs/" + target.replace(" ", "_")}>{prop}</Link></li>)
		}
		return <div>
			<ul class="docsNav">
				{navmenu}
			</ul>
			<div class="docsMain">
				{this.state.markdown ?
					<Markdown markdown={this.state.markdown} markdownOpts={this.markdownOptions}/> : null}
			</div>
		</div>;
	}
}
