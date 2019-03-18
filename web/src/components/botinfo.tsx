import {Component, h} from "preact";

import * as io from "socket.io-client";

import config from "../config";
import {BotInfoPageProps} from "../components/props";
import {BotInfoPageState, AuthObject, BotStats} from "../components/state";

export default class InfoPage extends Component<BotInfoPageProps, BotInfoPageState> {
    statsSocket: SocketIOClient.Socket;
    localAuthObject: AuthObject;
    timeCalcKeeper: number;

    componentDidMount() {
        this.statsSocket = io(config.apiUrl+"/api/botstats", {
            path: config.socketPath
        });

        this.localAuthObject = {
			client_id: window.localStorage.getItem("client_id"),
			client_token: window.localStorage.getItem("client_token"),
			timestamp: window.localStorage.getItem("auth_timestamp")
        }
        
        this.statsSocket.on("connect", () => {
			console.log(this.localAuthObject)
			this.statsSocket.emit("get", {
				"client_id": this.localAuthObject.client_id,
				"client_token": this.localAuthObject.client_token,
				"auth_timestamp": this.localAuthObject.timestamp
			})
			console.log("Connected to the bot statistics socket!");
			
        });
        
        this.statsSocket.on("api_response", (stats) => {
            this.setState({
                uptimeCount: stats[0],
                commandCount: stats[1],
                messageCount: stats[2],
                guildCount: stats[3],
                errorCount: stats[4],
                userCount: stats[5],
                uniqueUserCount: stats[6],
                tacoTime: stats[7],
                initalLoadDone: true
            });  
        });
    };

    render() {
        if (!this.state.initalLoadDone) {
			return (<h1 id="statsLoading">Loading bot stats...</h1>)
		} else { return (
            <div class="botInfoPage">
                <h2>Gearbot Information</h2>
                <table class="statsTable">
                    <td>
                        <tr>Uptime: {this.state.uptimeCount}</tr>
                        <tr>Messages Received: {this.state.messageCount}</tr>
                        <tr>Errors Encountered: {this.state.errorCount}</tr>
                    </td>
                    <td>
                        <tr>Commands Executed: {this.state.commandCount}</tr>
                        <tr>Guild Count: {this.state.guildCount}</tr>
                        <tr>User Count: {this.state.userCount} ({this.state.uniqueUserCount} were unique!)</tr>
                    </td>
                    <tr id="tacoTime">Taco Time! : {this.state.tacoTime} could of been eaten by the users in this time!</tr>
                </table>
            </div>
        )}
    }
}
