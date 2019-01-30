import {Component, h} from "preact";
import {Router} from "preact-router";

import Header from "./header";
// Code-splitting is automated for routes
import Home from "../routes/home";
import Dashboard from "../routes/dashboard";
import Docs from "../routes/docs";

import {DashboardState} from "./state";
import Gear from "./gear";

export default class App extends Component<{}, DashboardState> {
	handleRoute = (e: { url: string; }) => {
		this.setState({
			currentUrl: e.url
		});
	};

	render() {
		return (
			<div id="app">
				<Header image="https://cdn.discordapp.com/avatars/106354106196570112/097e0f5e83f747e5ae684f9180eb6dba.png?size=128"/>
					<Router onChange={this.handleRoute}>
						<Home path="/" />
						<Dashboard path="/dashboard"/>
						<Docs path="/docs/:folder?/:doc?"/>
					</Router>
				<div class="gearFooter">
					<Gear size={500}/>
				</div>
				</div>
		);
	}
}
