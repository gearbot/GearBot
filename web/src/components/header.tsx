import { h, Component } from "preact";
import { Link } from "preact-router";

import { HeaderProps } from "./props";
import { HeaderState } from "./state";

import Gear from "./gear";

export default class Header extends Component<HeaderProps, HeaderState> {
	constructor(props: HeaderProps, state: HeaderState) {
		super(props, state);
	}
	render() {
		return <header class="header">
			<Gear image={this.props.image}/>
			<h1>GearBot</h1>
			<div class="bar" />
			<nav>
				<Link activeClassName="active" href="/">Home</Link>
				<Link activeClassName="active" href="/servers">Me</Link>
			</nav>
		</header>;
	}
}
