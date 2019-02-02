import {Component, h} from "preact";
import {route, Router} from "preact-router";

import Header from "./header";
// Code-splitting is automated for routes
import Home from "../routes/home";
import Dashboard from "../routes/dashboard";
import Docs from "../routes/docs";

import {DashboardState} from "./state";
import Gear from "./gear";
import Error404 from "./Error404";

export default class App extends Component<{}, DashboardState> {

	componentDidMount(): void {
		addEventListener("click", this.cheat);
		addEventListener("touch", this.cheat);
	}

	cheat(e) {
		var a = e.target;
		if (a.tagName == "A") {
			let target = a.getAttribute("href");
			if (target.startsWith("/docs")) {
				route(target);
				e.preventDefault();
				e.stopImmediatePropagation();
				e.stopPropagation();
				return false;
			}
		}
	}


	handleRoute = (e: { url: string; }) => {
		this.setState({
			currentUrl: e.url
		});
	};

	render() {
		return (
			<div id="app">
				<Header />
				<Router onChange={this.handleRoute}>
					<Home path="/"/>
					<Dashboard path="/dashboard"/>
					<Docs path="/docs/" doc="index"/>
					<Docs path="/docs/:folder?/:doc?"/>

					<Error404 default/>
				</Router>
				<div class="gearFooter">
					<Gear size={500}/>
				</div>
			</div>
		);
	}
}
