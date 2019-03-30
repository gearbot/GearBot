import {Component, h} from "preact";

import * as io from "socket.io-client";

import config from "../config";
import {BotInfoPageProps} from "./props";
import {BotInfoPageState, AuthObject, BotStats} from "./state";

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
        
        this.statsSocket.once("connect", () => {
			console.log(this.localAuthObject)
			this.statsSocket.emit("get", {
				"client_id": this.localAuthObject.client_id,
				"client_token": this.localAuthObject.client_token,
				"auth_timestamp": this.localAuthObject.timestamp
			})
			console.log("Connected to the bot statistics socket!");
			this.setState({
                socketConnected: true
            });
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

        this.statsSocket.on("disconnect", () => {
            console.log("Lost connection to the WebSocket!")
            this.setState({
                socketConnected: false
            });
        });
    };

    componentWillUnmount() {
        this.statsSocket.close()
        console.log("Closed bot info socket!")
    }

    render() {
        if (!this.state.initalLoadDone) {
            return (<h1 id="statsLoading">Loading bot stats...</h1>)
        } else if (!this.state.socketConnected) {
            return (<h1 id="statsLoading">Failed to connect to the WebSocket!</h1>)
		} else { return (
            <div class="botInfoPage">
                <h2>Gearbot Information</h2>
                <table class="statsTable">
                    <tr>
                        <td>Uptime: {this.state.uptimeCount}</td>
                        <td>Messages Received: {this.state.messageCount}</td>
                        <td>Errors Encountered: {this.state.errorCount}</td>
                    </tr>
                    <tr>
                        <td>Commands Executed: {this.state.commandCount}</td>
                        <td>Guild Count: {this.state.guildCount}</td>
                        <td>User Count: {this.state.userCount} ({this.state.uniqueUserCount} were unique!)</td>
                    </tr>
                    <tr id="tacoTime">Taco Time! : {this.state.tacoTime} could of been eaten by the users in this time!</tr>
                </table>
            </div>
        )}
    }
}
