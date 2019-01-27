import {Component, h} from "preact";

import {GearProps} from "./props";
import {GearState} from "./state";

export default class Gear extends Component<GearProps, GearState> {

	constructor(props, state) {
		super(props, state);

		this.setState({
			rotation: 0,
			spinning: false
		});
	}



	startSpin() {
		console.log("starting spin")
		this.setState({spinning: true, rotation: this.state.rotation});
		requestAnimationFrame(() => this.spin());
	}
	spin() {
		console.log("spinning");
		this.setState({rotation: this.state.rotation + 2, spinning: this.state.spinning});
		if (this.state.spinning)
			requestAnimationFrame(this.spin);
	}

	endSpin() {
		this.setState({spinning: false, rotation: this.state.rotation})
	}


	render() {
		return (
			<div class="gearContainer" style={"width:" + this.props.size + "px;height:" + this.props.size + "px;"} >
				<img class="gear" src="assets/gear.svg" style={"transform:rotate(" + this.state.rotation + "deg);"} />
				{this.props.image ? <img class="gearImage" src={this.props.image} /> : null}
			</div>
		);
	}
}
