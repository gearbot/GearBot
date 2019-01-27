import {Component, h} from "preact";
import LeftNav from "../components/leftnav";


export default class Dashboard extends Component<{}, {}> {
    render() {
        return <div class="dashboard">
            <LeftNav/>
            <div class="dash-content">
                <h1>Dashboard</h1>
                <p>WIP</p>
            </div>

        </div>;
    }
}
