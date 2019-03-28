import {h, Component} from "preact";
import * as io from "socket.io-client";

import {GuildPageProps} from "./props";
import {GuildPageState, GuildPageStats, AuthObject} from "./state";
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
            console.log(recvStats)
            this.setState({
                guildPageStats: recvStats
            });
            console.log("Why: " + this.state.guildPageStats);
            // This is currently broken. For some reason the state part is undefined, causing the page to never load.
            // The data comes through the socket though as recvStats just fine :/
        });

        this.setState({
            initalLoadDone: true
        });
    }

    render() {
        if (!this.state.initalLoadDone) {
            return (<h1 id="statsLoading">Loading guild information...</h1>)
		} else { return (
            <div class="guildPage">
                <h2>{this.state.guildPageStats.name} + Information</h2>
                <h3>Guild ID: {this.state.guildPageStats.id}</h3>
                <table class="statsTable">
                    <td>
                        <tr>Owner: {this.state.guildPageStats.owner}</tr>
                        <tr>Members: {this.state.guildPageStats.memberCount}</tr>
                        <tr>Member Statuses: {this.state.guildPageStats.memberStatuses}</tr>
                    </td>
                    <td>
                        <tr>Text Channels: {this.state.guildPageStats.textChannels}</tr>
                        <tr>Voice Channels: {this.state.guildPageStats.voiceChannels}</tr>
                        <tr>Total Channels: {this.state.guildPageStats.totalChannels}</tr>
                    </td>
                    <td>
                        <tr>VIP Features: {this.state.guildPageStats.vipFeatures}</tr>
                        <tr>Creation Date: {this.state.guildPageStats.creationDate}</tr>
                        <tr>Server Icon URL: {this.state.guildPageStats.serverIcon}</tr>
                        <tr>Server Emote Count: {this.state.guildPageStats.serverEmoteCount}</tr>
                        
                    </td>
                    <tr>Roles: {this.state.guildPageStats.roles}</tr>
                </table>
            </div>
        )}
    }
}