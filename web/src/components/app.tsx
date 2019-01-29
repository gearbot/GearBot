import {Component, h} from "preact";
import {BrowserRouter as Router, Link, Route} from "react-router-dom";

import Header from "./header";
// Code-splitting is automated for routes
import Home from "../routes/home";
import Dashboard from "../routes/dashboard";
import Docs from "../routes/docs";

import {DashboardState} from "./state";
import Gear from "./gear";

export default class App extends Component<{}, DashboardState> {
	handleRoute = e => {
		this.setState({
			currentUrl: e.url
		});
	};

	render() {
		return (
			<div id="app">
				<Router>
					<div>
						<Header
							image="https://cdn.discordapp.com/avatars/106354106196570112/097e0f5e83f747e5ae684f9180eb6dba.png?size=128"/>
						<Route path="/" component={Home}/>
						<Route path="/dashboard" component={Dashboard}/>
						<Route path="/docs/:folder?/:doc?/" component={Docs}/>
					</div>
				</Router>
				<div class="gearFooter">
					<Gear size={500}/>
				</div>
			</div>


		);
	}
}
