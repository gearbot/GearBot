import {Component, h} from "preact";
import Markdown from "preact-markdown";
import {Docprops} from "../components/props";
import {DocState} from "../components/state";


export default class Docs extends Component<Docprops, DocState> {

	componentDidMount() {
		let url;
		console.log(this.props)
		if (this.props.doc == "")
			if (this.props.folder == "")
				url = "index.md";
			else
				url = this.props.folder + ".md";
		else
			url = this.props.doc + ".md";
		fetch(url).then(data => {
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
		return <div>
			<ul class="docsNav">

			</ul>
			<div class="docsMain">
				{this.state.markdown ?
					<Markdown markdown={this.state.markdown} markdownOpts={this.markdownOptions}/> : null}
			</div>
		</div>;
	}
}
