import { h, Component } from 'preact';
import style from './style';

class Gear extends Component {
	state = {
		rotation: 0,
        image: false,
        timer: false
	};

	getWidthStyle() {
		return 'width: 150px; height:150px;';
	};
	
	render() {
		return (
			<div class={style.gearContainer} style={this.getWidthStyle()}>
				<img class={style.gear} src="assets/gear.svg" />
				{this.props.image ? <img class={style.gearImage} src={this.props.image} /> : null}
			</div>
		);
	}
}

export default Gear;
