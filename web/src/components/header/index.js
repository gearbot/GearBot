import { h } from 'preact';
import { Link } from 'preact-router/match';
import style from './style';
import Gear from '../gear'

const Header = () => (
	<header class={style.header}>
        <Gear image="https://cdn.discordapp.com/avatars/106354106196570112/097e0f5e83f747e5ae684f9180eb6dba.webp?size=1024" />
		<h1>GearBot</h1>
		<div class={style.bar} />
		<nav>
			<Link activeClassName={style.active} href="/">Home</Link>
			<Link activeClassName={style.active} href="/servers">Me</Link>
		</nav>
	</header>
);

export default Header;
