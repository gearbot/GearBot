import {Component, h} from "preact";
import {route, Router} from "preact-router";

import * as io from "socket.io-client";

import config from "../config";

import Header from "./header";
import Home from "../routes/home";
import Dashboard from "../routes/dashboard";
import Docs from "../routes/docs";

import {DashboardState, InitalAuthObject} from "./state";
import Gear from "./gear";
import Error404 from "./Error404";

export default class App extends Component<{}, DashboardState> {
	mainAuthObject: InitalAuthObject

	componentDidMount(): void {
		const registrationSocket = io(config.apiUrl+"/api/", {
			path: config.socketPath
		});

		registrationSocket.emit("register_client", window.localStorage.getItem("auth_timestamp"));

		registrationSocket.once("api_response/registrationID", (RecAuthObject: InitalAuthObject) => {

			registrationSocket.close()
			console.log("Closed the inital auth socket!")

			if (RecAuthObject.status == "AUTH_SET") {
				this.mainAuthObject = RecAuthObject;
				window.localStorage.setItem("client_id", RecAuthObject.client_id)
				window.localStorage.setItem("client_token", RecAuthObject.client_token)
				window.localStorage.setItem("auth_timestamp", RecAuthObject.timestamp)
			} else {
				this.mainAuthObject = RecAuthObject;
			}
		});

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
					<Dashboard SocketAuthObject={this.mainAuthObject} path="/dashboard"/>
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
