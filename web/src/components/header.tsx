import {Component, h} from "preact";

import {HeaderProps} from "./props";
import {HeaderState} from "./state";
import {Link} from "react-router-dom";
import Gear from "./gear";

export default class Header extends Component<HeaderProps, HeaderState> {
    constructor(props: HeaderProps, state: HeaderState) {
        super(props, state);
    }

    render() {
        return <header class="header">
            <img src="assets/gearbot.png" class="gearbot"/>
            <h1>GearBot</h1>
            <div class="bar">
                <nav>
                    <Link activeClassName="active" to="/">Home</Link>
                    <Link activeClassName="active" to="/dashboard">Dashboard</Link>
                    <Link activeClassName="active" to="/docs">Docs</Link>
                    <div class="profileGear">
                        <Gear image={this.props.image} size={150}/>
                    </div>
                </nav>
            </div>
        </header>
    }
}
