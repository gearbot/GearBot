import {Component, h} from "preact";
import {Link} from "preact-router";

import * as io from "socket.io-client";

import {GuildNavProps} from "./props";
import {GuildListNavState, AuthObject} from "./state";
import {GuildListObject} from "./state";

import Gear from "./gear";

import config from "../config";
import {getCookie} from "./common";

export default class GuildNav extends Component<GuildNavProps, GuildListNavState> {
	guildSocket: SocketIOClient.Socket;
	generalSocket: SocketIOClient.Socket;

	LocalAuthObject: AuthObject;

	componentDidMount() {
		this.setState({
			guilds: [],
			guildsLoaded: false
		});

		this.generalSocket = io(config.apiUrl+"/api/", {
			path: config.socketPath
		});
		this.guildSocket = io(config.apiUrl+"/api/guilds", {
			path: config.socketPath,
			
		});

		/*
		If the Dashboard's window is refreshed, the main app doesnt handle the auth values as
		technically it doesnt render again? Not sure but this fixes it.
		*/
		window.localStorage.setItem("user_auth_token", getCookie("userauthtoken")) // Can't be set on the homepage
		this.LocalAuthObject = {
			client_id: window.localStorage.getItem("client_id"),
			client_token: window.localStorage.getItem("client_token"),
			timestamp: window.localStorage.getItem("auth_timestamp"),
			user_auth_token: window.localStorage.getItem("user_auth_token")
		}

		this.generalSocket.on("api_response", data => {
			console.log(data)
			// TODO: Some stuff here
		});

		this.guildSocket.on("connect", () => {
			console.log(this.LocalAuthObject)
			this.guildSocket.emit("get", {
				"client_id": this.LocalAuthObject.client_id,
				"client_token": this.LocalAuthObject.client_token,
				"auth_timestamp": this.LocalAuthObject.timestamp,
				"user_auth_token": this.LocalAuthObject.user_auth_token
			})
			console.log("Connected to the API's guild data socket!");
			
		});
		this.guildSocket.on("api_response", (data: GuildListObject[]) => {
			console.log(data)
			this.setState({
				guilds: data,
				guildsLoaded: true
			})
		});
	}

	componentWillUnmount() {
		console.log("Closing dashboard sockets!") // Keeping tidy with our sockets
		this.guildSocket.close()
		this.generalSocket.close()
	}

	render() {
		if (!this.state.guildsLoaded) {
			return (<h1>Loading guilds...</h1>)
		} else {
			let selections = [];
			for (let guild in this.state.guilds) {
				let info = this.state.guilds[guild];
				console.log(info.name + " Auth Status: " + info.authorized)
				selections.push(
					<div class="guildSelection" style={info.authorized == true ? "": "opacity: 0.5"}>
						<Link href={"/dashboard/" + guild} activeClassName={"active"}>
							<Gear size={250} image={info.icon}/>
							<p>{info.name}</p>
						</Link>
					</div>
				)
			}
			return (
				<div class="guild-nav">
					{selections.length > 0 ? selections :
						<div class="noGuildsFoundMessage">No guilds currently avaliable!</div>}
				</div>
			)
		}
	}

}