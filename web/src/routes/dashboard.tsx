import {Component, h} from "preact";
import GuildNav from "../components/guildnav";
import AntiRaidBuilder from "../components/antiraid";
import InfoPage from "../components/botinfo";

import {DashboardProps} from "../components/props";
import config from "../config";

export default class Dashboard extends Component<DashboardProps, {}> {
    render() {
        return <div class="dashboard">
            <a href={"http://"+config.apiUrl+"/discord/login"} id="discordSignIn">
                Sign In
            </a>
            {/* Im thinking that the stats page can be up as the default when you go here and a side menu presents other
            options to the user, such as anti-raid, moderation, logs, etc. */}
            {/* <GuildNav SocketAuthObject={this.props.SocketAuthObject}></GuildNav> */}
            {/*<AntiRaidBuilder></AntiRaidBuilder>*/}
            <InfoPage SocketAuthObject={this.props.SocketAuthObject}></InfoPage>
            <div class="dash-content">
                {/*<h1>Dashboard</h1>*/}
            </div>
        </div>;
    }
}
 