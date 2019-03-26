import {Component, h} from "preact";
import Markdown from "preact-markdown";
import {Docprops} from "../components/props";
import {DocState} from "../components/state";
import menu from "../docs/menu"
import {Link} from "preact-router/match";


export default class Docs extends Component<Docprops, DocState> {
	updating = false


	componentDidMount(): void {
		this.update(this.props)
	}

	markdownOptions = {
		"headerIds": true,
		"breaks": true
	};

	update(props) {
		if (this.updating)
			return;
		this.updating = true;
		let link = this.getLink(props);
		fetch(link).then(data => {
			console.log("We made a request and got a code of " + data.status);
			if (data.status == 200) {
				data.text().then(text => {
					this.setState({markdown: text, link: link});
					this.updating = false
				})
			} else {
				this.setState({markdown: "# 404", link: link});
				this.updating = false
			}
		});
	}


	componentWillUpdate(nextProps: Readonly<Docprops>, nextState: Readonly<DocState>, nextContext: any): void {
		if (this.getLink(nextProps) != this.state.link && this.state.link != undefined && !this.updating)
			this.update(nextProps);
	}


	getLink(state): string {
		let url: RequestInfo;
		if (state.doc == "")
			if (state.folder == "")
				url = "index.md";
			else
				url = state.folder + ".md";
		else
			url = state.doc + ".md";
		return url;
	}

	render({doc}) {
		let navmenu = [];
		for (let prop in menu) {
			let value = menu[prop];
			if (typeof value == "string") {
				navmenu.push(<li class="navItem"><Link activeClassName={"active"}
				    href={"/docs/" + value.replace(" ", "_")}>{prop}</Link>
				</li>)
			} else {
				let items = [];
				for (let prop2 in value) {
					let value2 = value[prop2];
					items.push(<li class="navItem"><Link activeClassName={"active"}
					    href={"/docs/" + value2}>{prop2}</Link></li>)
				}

				navmenu.push(<li class="navItem"><div>{prop}</div></li>);
				navmenu.push(<li style="list-style:none;">
					<ul>{items}</ul>
				</li>);
			}
		}
		return <div class="docwrapper">
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
