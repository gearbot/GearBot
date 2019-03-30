import {Component, h} from "preact";
import * as io from "socket.io-client";

import {GuildPageProps} from "./props";
import {AuthObject, GuildPageState, GuildPageStats} from "./state";
import config from "../config";

export default class GuildPage extends Component<GuildPageProps, GuildPageState> {
    guildInfoSocket: SocketIOClient.Socket;
    localAuthObject: AuthObject;


    componentDidMount() {
        this.guildInfoSocket = io(config.apiUrl+"/api/guildpage", {
            path: config.socketPath
        });

        this.localAuthObject = {
			client_id: window.localStorage.getItem("client_id"),
			client_token: window.localStorage.getItem("client_token"),
			timestamp: window.localStorage.getItem("auth_timestamp")
        }
        
        this.guildInfoSocket.on("connect", () => {
			console.log(this.localAuthObject)
			this.guildInfoSocket.emit("get", {
				"client_id": this.localAuthObject.client_id,
				"client_token": this.localAuthObject.client_token,
				"auth_timestamp": this.localAuthObject.timestamp
			})
			console.log("Connected to the guild page info socket!");
        });
        
        this.guildInfoSocket.on("api_response", (recvStats: GuildPageStats) => {
            console.log(recvStats);
            this.setState({
                guildPageStats: recvStats
            });
        });
    }

    render() {
        if (!this.state.guildPageStats) {
            return (<h1 id="statsLoading">Loading guild information...</h1>)
		} else {
            const statuses = this.state.guildPageStats.memberStatuses
            const vipFeatures = this.state.guildPageStats.vipFeatures
            return ( // This loads and then crashes with a error in the browser console.
            <div class="guildPage">
                <h2>{this.state.guildPageStats.name} Information</h2>
                <h3>Guild ID: {this.state.guildPageStats.id}</h3>
                <table class="statsTable">
                    <tr>
                        <td>Owner: {this.state.guildPageStats.owner}</td>
                        {console.log(this.state.guildPageStats.vipFeatures)}
                        <td>Members: {this.state.guildPageStats.memberCount}</td>
                    </tr>
                    <tr>
                        Member Statuses:
                        <tr id="statusTable">
                            <td>Online: {statuses.online}</td>
                            <td>Idle: {statuses.idle}</td>
                            <td>DnD: {statuses.dnd}</td>
                            <td>Offline: {statuses.dnd}</td>
                        </tr>
                    </tr>
                    <tr>
                        <td>Text Channels: {this.state.guildPageStats.textChannels}</td>
                        <td>Voice Channels: {this.state.guildPageStats.voiceChannels}</td>
                        <td>Total Channels: {this.state.guildPageStats.totalChannels}</td>
                    </tr>
                    <tr>
                        <td>VIP Features: {vipFeatures ? "True" : "False"}</td>
                        <td>Creation Date: {this.state.guildPageStats.creationDate}</td>
                        <td>Server Icon URL: {this.state.guildPageStats.serverIcon}</td>
                        <td>Server Emote Count: {this.state.guildPageStats.serverEmoteCount}</td>
                        
                    </tr>
                    <tr>Roles: {this.state.guildPageStats.roles}</tr>
                </table>
            </div>
        )}
    }
}