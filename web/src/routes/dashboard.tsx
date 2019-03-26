import {Component, h} from "preact";
import {Link} from "preact-router";

import GuildNav from "../components/guildnav";
import AntiRaidBuilder from "../components/antiraid";
import InfoPage from "../components/botinfo";

import {DashboardProps} from "../components/props";
import {DashboardState} from "../components/state";
import config from "../config";

export default class Dashboard extends Component<DashboardProps, DashboardState> {
    componentDidMount() {
        this.setState({ // Default here
            currentComponent: <InfoPage SocketAuthObject={this.props.SocketAuthObject}></InfoPage>
        });
    };

    changeDashComponent(selection: JSX.Element) {
        this.setState({
            currentComponent: selection
        });
    };

    render() {
        return <div class="dashboard">
            <a href={"http://"+config.apiUrl+"/discord/login"} id="discordSignIn">
                Sign In
            </a>

            { this.state.currentComponent }

            <ul class="dashboardSideNav">
                <li class="navItem"><Link activeClassName={"active"} href="/dashboard/"
                    onClick={() => this.changeDashComponent(<InfoPage SocketAuthObject={this.props.SocketAuthObject}></InfoPage>)}>
                    Home and Statistics
                </Link></li>

                <li class="navItem"><Link activeClassName={"active"} href="/dashboard/"
                    onClick={() => this.changeDashComponent(<GuildNav SocketAuthObject={this.props.SocketAuthObject}></GuildNav>)}>
                    Guilds
                </Link></li>
                
                {/* AntiRaid will probably go under per-guild later, but its easy to access here for now */}
                <li class="navItem"><Link activeClassName={"active"} href="/dashboard/"
                    onClick={() => this.changeDashComponent(<AntiRaidBuilder></AntiRaidBuilder>)}>
                    AntiRaid
                </Link></li>
            </ul>
        </div>
    }
}
 