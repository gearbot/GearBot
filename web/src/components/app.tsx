import {Component, h} from "preact";
import {route, Router} from "preact-router";

import Header from "./header";
// Code-splitting is automated for routes
import Home from "../routes/home";
import Dashboard from "../routes/dashboard";
import Docs from "../routes/docs";

import {DashboardState} from "./state";
import Gear from "./gear";

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
				<Header
					image="https://cdn.discordapp.com/avatars/106354106196570112/097e0f5e83f747e5ae684f9180eb6dba.png?size=128"/>
				<Router onChange={this.handleRoute}>
					<Home path="/"/>
					<Dashboard path="/dashboard"/>
					<Docs path="/docs/" doc="index"/>
					<Docs path="/docs/:folder?/:doc?"/>
				</Router>
				<div class="gearFooter">
					<Gear size={500}/>
				</div>
			</div>
		);
	}
}
