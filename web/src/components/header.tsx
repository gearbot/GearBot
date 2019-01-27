import {Component, h} from "preact";
import {Link} from "preact-router";

import {HeaderProps} from "./props";
import {HeaderState} from "./state";

import Gear from "./gear";

export default class Header extends Component<HeaderProps, HeaderState> {
    constructor(props: HeaderProps, state: HeaderState) {
        super(props, state);
    }

    render() {
        return <header class="header">
            <img src="https://cdn.discordapp.com/emojis/529008659498270721.png?v=1" class="gearbot"/>
            <h1>GearBot</h1>
            <div class="bar">
                <nav>
                    <Link activeClassName="active" href="/">Home</Link>
                    <Link activeClassName="active" href="/servers">Server list</Link>
                    <div class="profileGear">
                        <Gear image={this.props.image} size={150}/>
                    </div>
                </nav>
            </div>
        </header>;
    }
}
