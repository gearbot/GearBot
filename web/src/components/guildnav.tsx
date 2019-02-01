import {Component, h} from "preact";
import {Link} from "preact-router";

import * as io from "socket.io-client";

import {GuildListNavState} from "./state";

import Gear from "./gear";

import config from "../config";

export default class GuildNav extends Component<{}, GuildListNavState> {
	guildSocket: SocketIOClient.Socket;
	generalsocket: SocketIOClient.Socket;
	apiUrl: string;

	constructor(props, state) {
		super(props, state);

		this.apiUrl = config.apiUrl;

		this.setState({
			guilds: [],
			guildsLoaded: false
		});

		this.guildSocket = io(this.apiUrl+"/api/guilds", {
			path: "/ws"
        });

		this.generalsocket = io(this.apiUrl+"/api/", {
			path: "/ws"
		})

		this.guildSocket.on("connect", () => {
			this.guildSocket.emit("get", "")
			console.log("Connected to the API's guild data socket!");
			
		})

		this.generalsocket.on("api_response", data => console.log(data));
		
		this.guildSocket.on("api_response", data => {
			console.log(data)
			this.setState({
				guilds: data,
				guildsLoaded: true
			})
		});
	}

	render() {
		if (!this.state.guildsLoaded) {
			return (<h1>Loading guilds...</h1>)
		} else {
			let selections = [];
			for (let guid in this.state.guilds) {
				let info = this.state.guilds[guid];
				selections.push(
					<div class="guildSelection">
						<Link href={"/dashboard/" + guid} activeClassName={"active"}>
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