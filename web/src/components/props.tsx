import {AuthObject} from "./state";

export interface HeaderProps {
	image?: string;
}

export interface GearProps {
	image?: string;
	size: number;
}

export interface Docprops {
	doc?: string,
	folder?: string
}

export interface AntiraidProps {

}

interface Socketed {
	SocketAuthObject: AuthObject;
}

export interface DashboardProps extends Socketed {}

export interface GuildNavProps extends Socketed {}