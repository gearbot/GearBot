import {Component, h} from "preact";
import GuildNav from "../components/guildnav";


export default class Dashboard extends Component<{}, {}> {
    render() {
        return <div class="dashboard">
            <GuildNav/>
            <div class="dash-content">
                <h1>Dashboard</h1>
            </div>
        </div>;
    }
}
