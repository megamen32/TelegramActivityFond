import LikeTask
import utils
import yappyUser

max_tasks_in_level=300
start_task_count=3
TASKS_TO_NEXT_LEVEL={level:int(max(level,min(level*max_tasks_in_level,pow(4,level))) ) if level < 4 else max_tasks_in_level*(level-4)+256 for level in range(1,100)}
BONUS_FOR_NEXT_LEVEL={level: level if level<=10 else 20 for level in range(1,100)}
def get_level(user:yappyUser.YappyUser):
    task_complete=len(user.done_tasks)
    level=0
    tasks_to_next_level=start_task_count
    level=0
    exp=tasks_to_next_level
    for level,exp in TASKS_TO_NEXT_LEVEL.items():
        if exp>task_complete:
            break
    level=max(0,level-1)
    user.tasks_to_next_level=exp-task_complete
    new_level=False
    if level>user.level:
        new_level=True
    user.level=level
    return new_level



