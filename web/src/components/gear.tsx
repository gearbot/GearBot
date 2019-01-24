import { h, Component } from "preact";

import { GearProps } from "./props";
import { GearState } from "./state";

export default class Gear extends Component<GearProps, GearState> {

	constructor(props, state) {
		super(props, state);

		this.setState({
			rotation: 0,
			// image: "",
			timer: 0
		});
	}

	render() {
		return (
			<div class="gearContainer" style="width: 150px; height:150px;">
				<img class="gear" src="assets/gear.svg" />
				{this.props.image ? <img class="gearImage" src={this.props.image} /> : null}
			</div>
		);
	}
}
