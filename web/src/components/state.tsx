export interface GearState {
	rotation: number;
	spinning: boolean;
}

export interface DashboardState {
	currentUrl: string;
}

export interface HeaderState {

}

export interface GuildListNavState {
	guilds: GuildListObject[];
	guildsLoaded: boolean;
}

export interface GuildListObject {
	name: string;
	icon: string;
}

export interface DocState {
	markdown: string,
	link: string
}

export interface AuthObject {
	client_id: string;
	timestamp: string;
	client_token?: string;
	errorValue?: number;
}

export interface InitalAuthObject extends AuthObject {
	status: string;
}
