import {Component, h} from "preact";
import {Link} from "react-router-dom";

export default class LeftNav extends Component<{}, {}> {


    render() {
        return (
            <div class="left-nav">
                <ul>
                    <li><Link to="/dashboard/test/1" activeClassName={"active"}>Test 1</Link></li>
                    <li><Link to="/dashboard/test/2" activeClassName={"active"}>Test 2</Link></li>
                    <li><Link to="/dashboard/test/3" activeClassName={"active"}>Test 3</Link></li>
                    <li><Link to="/dashboard/test/4" activeClassName={"active"}>Test 4</Link></li>
                </ul>
            </div>

        );
    }

}